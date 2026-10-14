#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_2545601134011040542) {
   out_2545601134011040542[0] = delta_x[0] + nom_x[0];
   out_2545601134011040542[1] = delta_x[1] + nom_x[1];
   out_2545601134011040542[2] = delta_x[2] + nom_x[2];
   out_2545601134011040542[3] = delta_x[3] + nom_x[3];
   out_2545601134011040542[4] = delta_x[4] + nom_x[4];
   out_2545601134011040542[5] = delta_x[5] + nom_x[5];
   out_2545601134011040542[6] = delta_x[6] + nom_x[6];
   out_2545601134011040542[7] = delta_x[7] + nom_x[7];
   out_2545601134011040542[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_8461508002424427576) {
   out_8461508002424427576[0] = -nom_x[0] + true_x[0];
   out_8461508002424427576[1] = -nom_x[1] + true_x[1];
   out_8461508002424427576[2] = -nom_x[2] + true_x[2];
   out_8461508002424427576[3] = -nom_x[3] + true_x[3];
   out_8461508002424427576[4] = -nom_x[4] + true_x[4];
   out_8461508002424427576[5] = -nom_x[5] + true_x[5];
   out_8461508002424427576[6] = -nom_x[6] + true_x[6];
   out_8461508002424427576[7] = -nom_x[7] + true_x[7];
   out_8461508002424427576[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_704917235979003887) {
   out_704917235979003887[0] = 1.0;
   out_704917235979003887[1] = 0.0;
   out_704917235979003887[2] = 0.0;
   out_704917235979003887[3] = 0.0;
   out_704917235979003887[4] = 0.0;
   out_704917235979003887[5] = 0.0;
   out_704917235979003887[6] = 0.0;
   out_704917235979003887[7] = 0.0;
   out_704917235979003887[8] = 0.0;
   out_704917235979003887[9] = 0.0;
   out_704917235979003887[10] = 1.0;
   out_704917235979003887[11] = 0.0;
   out_704917235979003887[12] = 0.0;
   out_704917235979003887[13] = 0.0;
   out_704917235979003887[14] = 0.0;
   out_704917235979003887[15] = 0.0;
   out_704917235979003887[16] = 0.0;
   out_704917235979003887[17] = 0.0;
   out_704917235979003887[18] = 0.0;
   out_704917235979003887[19] = 0.0;
   out_704917235979003887[20] = 1.0;
   out_704917235979003887[21] = 0.0;
   out_704917235979003887[22] = 0.0;
   out_704917235979003887[23] = 0.0;
   out_704917235979003887[24] = 0.0;
   out_704917235979003887[25] = 0.0;
   out_704917235979003887[26] = 0.0;
   out_704917235979003887[27] = 0.0;
   out_704917235979003887[28] = 0.0;
   out_704917235979003887[29] = 0.0;
   out_704917235979003887[30] = 1.0;
   out_704917235979003887[31] = 0.0;
   out_704917235979003887[32] = 0.0;
   out_704917235979003887[33] = 0.0;
   out_704917235979003887[34] = 0.0;
   out_704917235979003887[35] = 0.0;
   out_704917235979003887[36] = 0.0;
   out_704917235979003887[37] = 0.0;
   out_704917235979003887[38] = 0.0;
   out_704917235979003887[39] = 0.0;
   out_704917235979003887[40] = 1.0;
   out_704917235979003887[41] = 0.0;
   out_704917235979003887[42] = 0.0;
   out_704917235979003887[43] = 0.0;
   out_704917235979003887[44] = 0.0;
   out_704917235979003887[45] = 0.0;
   out_704917235979003887[46] = 0.0;
   out_704917235979003887[47] = 0.0;
   out_704917235979003887[48] = 0.0;
   out_704917235979003887[49] = 0.0;
   out_704917235979003887[50] = 1.0;
   out_704917235979003887[51] = 0.0;
   out_704917235979003887[52] = 0.0;
   out_704917235979003887[53] = 0.0;
   out_704917235979003887[54] = 0.0;
   out_704917235979003887[55] = 0.0;
   out_704917235979003887[56] = 0.0;
   out_704917235979003887[57] = 0.0;
   out_704917235979003887[58] = 0.0;
   out_704917235979003887[59] = 0.0;
   out_704917235979003887[60] = 1.0;
   out_704917235979003887[61] = 0.0;
   out_704917235979003887[62] = 0.0;
   out_704917235979003887[63] = 0.0;
   out_704917235979003887[64] = 0.0;
   out_704917235979003887[65] = 0.0;
   out_704917235979003887[66] = 0.0;
   out_704917235979003887[67] = 0.0;
   out_704917235979003887[68] = 0.0;
   out_704917235979003887[69] = 0.0;
   out_704917235979003887[70] = 1.0;
   out_704917235979003887[71] = 0.0;
   out_704917235979003887[72] = 0.0;
   out_704917235979003887[73] = 0.0;
   out_704917235979003887[74] = 0.0;
   out_704917235979003887[75] = 0.0;
   out_704917235979003887[76] = 0.0;
   out_704917235979003887[77] = 0.0;
   out_704917235979003887[78] = 0.0;
   out_704917235979003887[79] = 0.0;
   out_704917235979003887[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_237457952738950812) {
   out_237457952738950812[0] = state[0];
   out_237457952738950812[1] = state[1];
   out_237457952738950812[2] = state[2];
   out_237457952738950812[3] = state[3];
   out_237457952738950812[4] = state[4];
   out_237457952738950812[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_237457952738950812[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_237457952738950812[7] = state[7];
   out_237457952738950812[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4090080787877149803) {
   out_4090080787877149803[0] = 1;
   out_4090080787877149803[1] = 0;
   out_4090080787877149803[2] = 0;
   out_4090080787877149803[3] = 0;
   out_4090080787877149803[4] = 0;
   out_4090080787877149803[5] = 0;
   out_4090080787877149803[6] = 0;
   out_4090080787877149803[7] = 0;
   out_4090080787877149803[8] = 0;
   out_4090080787877149803[9] = 0;
   out_4090080787877149803[10] = 1;
   out_4090080787877149803[11] = 0;
   out_4090080787877149803[12] = 0;
   out_4090080787877149803[13] = 0;
   out_4090080787877149803[14] = 0;
   out_4090080787877149803[15] = 0;
   out_4090080787877149803[16] = 0;
   out_4090080787877149803[17] = 0;
   out_4090080787877149803[18] = 0;
   out_4090080787877149803[19] = 0;
   out_4090080787877149803[20] = 1;
   out_4090080787877149803[21] = 0;
   out_4090080787877149803[22] = 0;
   out_4090080787877149803[23] = 0;
   out_4090080787877149803[24] = 0;
   out_4090080787877149803[25] = 0;
   out_4090080787877149803[26] = 0;
   out_4090080787877149803[27] = 0;
   out_4090080787877149803[28] = 0;
   out_4090080787877149803[29] = 0;
   out_4090080787877149803[30] = 1;
   out_4090080787877149803[31] = 0;
   out_4090080787877149803[32] = 0;
   out_4090080787877149803[33] = 0;
   out_4090080787877149803[34] = 0;
   out_4090080787877149803[35] = 0;
   out_4090080787877149803[36] = 0;
   out_4090080787877149803[37] = 0;
   out_4090080787877149803[38] = 0;
   out_4090080787877149803[39] = 0;
   out_4090080787877149803[40] = 1;
   out_4090080787877149803[41] = 0;
   out_4090080787877149803[42] = 0;
   out_4090080787877149803[43] = 0;
   out_4090080787877149803[44] = 0;
   out_4090080787877149803[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4090080787877149803[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4090080787877149803[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4090080787877149803[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4090080787877149803[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4090080787877149803[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4090080787877149803[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4090080787877149803[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4090080787877149803[53] = -9.8100000000000005*dt;
   out_4090080787877149803[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4090080787877149803[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4090080787877149803[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4090080787877149803[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4090080787877149803[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4090080787877149803[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4090080787877149803[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4090080787877149803[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4090080787877149803[62] = 0;
   out_4090080787877149803[63] = 0;
   out_4090080787877149803[64] = 0;
   out_4090080787877149803[65] = 0;
   out_4090080787877149803[66] = 0;
   out_4090080787877149803[67] = 0;
   out_4090080787877149803[68] = 0;
   out_4090080787877149803[69] = 0;
   out_4090080787877149803[70] = 1;
   out_4090080787877149803[71] = 0;
   out_4090080787877149803[72] = 0;
   out_4090080787877149803[73] = 0;
   out_4090080787877149803[74] = 0;
   out_4090080787877149803[75] = 0;
   out_4090080787877149803[76] = 0;
   out_4090080787877149803[77] = 0;
   out_4090080787877149803[78] = 0;
   out_4090080787877149803[79] = 0;
   out_4090080787877149803[80] = 1;
}
void h_25(double *state, double *unused, double *out_8286540641341237964) {
   out_8286540641341237964[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2818063414010487790) {
   out_2818063414010487790[0] = 0;
   out_2818063414010487790[1] = 0;
   out_2818063414010487790[2] = 0;
   out_2818063414010487790[3] = 0;
   out_2818063414010487790[4] = 0;
   out_2818063414010487790[5] = 0;
   out_2818063414010487790[6] = 1;
   out_2818063414010487790[7] = 0;
   out_2818063414010487790[8] = 0;
}
void h_24(double *state, double *unused, double *out_7115619409547049932) {
   out_7115619409547049932[0] = state[4];
   out_7115619409547049932[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6375989012812810926) {
   out_6375989012812810926[0] = 0;
   out_6375989012812810926[1] = 0;
   out_6375989012812810926[2] = 0;
   out_6375989012812810926[3] = 0;
   out_6375989012812810926[4] = 1;
   out_6375989012812810926[5] = 0;
   out_6375989012812810926[6] = 0;
   out_6375989012812810926[7] = 0;
   out_6375989012812810926[8] = 0;
   out_6375989012812810926[9] = 0;
   out_6375989012812810926[10] = 0;
   out_6375989012812810926[11] = 0;
   out_6375989012812810926[12] = 0;
   out_6375989012812810926[13] = 0;
   out_6375989012812810926[14] = 1;
   out_6375989012812810926[15] = 0;
   out_6375989012812810926[16] = 0;
   out_6375989012812810926[17] = 0;
}
void h_30(double *state, double *unused, double *out_4004756236527653523) {
   out_4004756236527653523[0] = state[4];
}
void H_30(double *state, double *unused, double *out_1709632916117120408) {
   out_1709632916117120408[0] = 0;
   out_1709632916117120408[1] = 0;
   out_1709632916117120408[2] = 0;
   out_1709632916117120408[3] = 0;
   out_1709632916117120408[4] = 1;
   out_1709632916117120408[5] = 0;
   out_1709632916117120408[6] = 0;
   out_1709632916117120408[7] = 0;
   out_1709632916117120408[8] = 0;
}
void h_26(double *state, double *unused, double *out_3430387197901047290) {
   out_3430387197901047290[0] = state[7];
}
void H_26(double *state, double *unused, double *out_923439904863568434) {
   out_923439904863568434[0] = 0;
   out_923439904863568434[1] = 0;
   out_923439904863568434[2] = 0;
   out_923439904863568434[3] = 0;
   out_923439904863568434[4] = 0;
   out_923439904863568434[5] = 0;
   out_923439904863568434[6] = 0;
   out_923439904863568434[7] = 1;
   out_923439904863568434[8] = 0;
}
void h_27(double *state, double *unused, double *out_5158530164707468007) {
   out_5158530164707468007[0] = state[3];
}
void H_27(double *state, double *unused, double *out_513961155066822809) {
   out_513961155066822809[0] = 0;
   out_513961155066822809[1] = 0;
   out_513961155066822809[2] = 0;
   out_513961155066822809[3] = 1;
   out_513961155066822809[4] = 0;
   out_513961155066822809[5] = 0;
   out_513961155066822809[6] = 0;
   out_513961155066822809[7] = 0;
   out_513961155066822809[8] = 0;
}
void h_29(double *state, double *unused, double *out_4791553227738343617) {
   out_4791553227738343617[0] = state[1];
}
void H_29(double *state, double *unused, double *out_1199401571802728224) {
   out_1199401571802728224[0] = 0;
   out_1199401571802728224[1] = 1;
   out_1199401571802728224[2] = 0;
   out_1199401571802728224[3] = 0;
   out_1199401571802728224[4] = 0;
   out_1199401571802728224[5] = 0;
   out_1199401571802728224[6] = 0;
   out_1199401571802728224[7] = 0;
   out_1199401571802728224[8] = 0;
}
void h_28(double *state, double *unused, double *out_92112645989125284) {
   out_92112645989125284[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6281800588872258798) {
   out_6281800588872258798[0] = 1;
   out_6281800588872258798[1] = 0;
   out_6281800588872258798[2] = 0;
   out_6281800588872258798[3] = 0;
   out_6281800588872258798[4] = 0;
   out_6281800588872258798[5] = 0;
   out_6281800588872258798[6] = 0;
   out_6281800588872258798[7] = 0;
   out_6281800588872258798[8] = 0;
}
void h_31(double *state, double *unused, double *out_8011346579056732075) {
   out_8011346579056732075[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2848709375887448218) {
   out_2848709375887448218[0] = 0;
   out_2848709375887448218[1] = 0;
   out_2848709375887448218[2] = 0;
   out_2848709375887448218[3] = 0;
   out_2848709375887448218[4] = 0;
   out_2848709375887448218[5] = 0;
   out_2848709375887448218[6] = 0;
   out_2848709375887448218[7] = 0;
   out_2848709375887448218[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_2545601134011040542) {
  err_fun(nom_x, delta_x, out_2545601134011040542);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8461508002424427576) {
  inv_err_fun(nom_x, true_x, out_8461508002424427576);
}
void car_H_mod_fun(double *state, double *out_704917235979003887) {
  H_mod_fun(state, out_704917235979003887);
}
void car_f_fun(double *state, double dt, double *out_237457952738950812) {
  f_fun(state,  dt, out_237457952738950812);
}
void car_F_fun(double *state, double dt, double *out_4090080787877149803) {
  F_fun(state,  dt, out_4090080787877149803);
}
void car_h_25(double *state, double *unused, double *out_8286540641341237964) {
  h_25(state, unused, out_8286540641341237964);
}
void car_H_25(double *state, double *unused, double *out_2818063414010487790) {
  H_25(state, unused, out_2818063414010487790);
}
void car_h_24(double *state, double *unused, double *out_7115619409547049932) {
  h_24(state, unused, out_7115619409547049932);
}
void car_H_24(double *state, double *unused, double *out_6375989012812810926) {
  H_24(state, unused, out_6375989012812810926);
}
void car_h_30(double *state, double *unused, double *out_4004756236527653523) {
  h_30(state, unused, out_4004756236527653523);
}
void car_H_30(double *state, double *unused, double *out_1709632916117120408) {
  H_30(state, unused, out_1709632916117120408);
}
void car_h_26(double *state, double *unused, double *out_3430387197901047290) {
  h_26(state, unused, out_3430387197901047290);
}
void car_H_26(double *state, double *unused, double *out_923439904863568434) {
  H_26(state, unused, out_923439904863568434);
}
void car_h_27(double *state, double *unused, double *out_5158530164707468007) {
  h_27(state, unused, out_5158530164707468007);
}
void car_H_27(double *state, double *unused, double *out_513961155066822809) {
  H_27(state, unused, out_513961155066822809);
}
void car_h_29(double *state, double *unused, double *out_4791553227738343617) {
  h_29(state, unused, out_4791553227738343617);
}
void car_H_29(double *state, double *unused, double *out_1199401571802728224) {
  H_29(state, unused, out_1199401571802728224);
}
void car_h_28(double *state, double *unused, double *out_92112645989125284) {
  h_28(state, unused, out_92112645989125284);
}
void car_H_28(double *state, double *unused, double *out_6281800588872258798) {
  H_28(state, unused, out_6281800588872258798);
}
void car_h_31(double *state, double *unused, double *out_8011346579056732075) {
  h_31(state, unused, out_8011346579056732075);
}
void car_H_31(double *state, double *unused, double *out_2848709375887448218) {
  H_31(state, unused, out_2848709375887448218);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
