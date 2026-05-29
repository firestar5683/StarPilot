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
void err_fun(double *nom_x, double *delta_x, double *out_1972702472511725479) {
   out_1972702472511725479[0] = delta_x[0] + nom_x[0];
   out_1972702472511725479[1] = delta_x[1] + nom_x[1];
   out_1972702472511725479[2] = delta_x[2] + nom_x[2];
   out_1972702472511725479[3] = delta_x[3] + nom_x[3];
   out_1972702472511725479[4] = delta_x[4] + nom_x[4];
   out_1972702472511725479[5] = delta_x[5] + nom_x[5];
   out_1972702472511725479[6] = delta_x[6] + nom_x[6];
   out_1972702472511725479[7] = delta_x[7] + nom_x[7];
   out_1972702472511725479[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3741555659818717473) {
   out_3741555659818717473[0] = -nom_x[0] + true_x[0];
   out_3741555659818717473[1] = -nom_x[1] + true_x[1];
   out_3741555659818717473[2] = -nom_x[2] + true_x[2];
   out_3741555659818717473[3] = -nom_x[3] + true_x[3];
   out_3741555659818717473[4] = -nom_x[4] + true_x[4];
   out_3741555659818717473[5] = -nom_x[5] + true_x[5];
   out_3741555659818717473[6] = -nom_x[6] + true_x[6];
   out_3741555659818717473[7] = -nom_x[7] + true_x[7];
   out_3741555659818717473[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_4845788339544047954) {
   out_4845788339544047954[0] = 1.0;
   out_4845788339544047954[1] = 0.0;
   out_4845788339544047954[2] = 0.0;
   out_4845788339544047954[3] = 0.0;
   out_4845788339544047954[4] = 0.0;
   out_4845788339544047954[5] = 0.0;
   out_4845788339544047954[6] = 0.0;
   out_4845788339544047954[7] = 0.0;
   out_4845788339544047954[8] = 0.0;
   out_4845788339544047954[9] = 0.0;
   out_4845788339544047954[10] = 1.0;
   out_4845788339544047954[11] = 0.0;
   out_4845788339544047954[12] = 0.0;
   out_4845788339544047954[13] = 0.0;
   out_4845788339544047954[14] = 0.0;
   out_4845788339544047954[15] = 0.0;
   out_4845788339544047954[16] = 0.0;
   out_4845788339544047954[17] = 0.0;
   out_4845788339544047954[18] = 0.0;
   out_4845788339544047954[19] = 0.0;
   out_4845788339544047954[20] = 1.0;
   out_4845788339544047954[21] = 0.0;
   out_4845788339544047954[22] = 0.0;
   out_4845788339544047954[23] = 0.0;
   out_4845788339544047954[24] = 0.0;
   out_4845788339544047954[25] = 0.0;
   out_4845788339544047954[26] = 0.0;
   out_4845788339544047954[27] = 0.0;
   out_4845788339544047954[28] = 0.0;
   out_4845788339544047954[29] = 0.0;
   out_4845788339544047954[30] = 1.0;
   out_4845788339544047954[31] = 0.0;
   out_4845788339544047954[32] = 0.0;
   out_4845788339544047954[33] = 0.0;
   out_4845788339544047954[34] = 0.0;
   out_4845788339544047954[35] = 0.0;
   out_4845788339544047954[36] = 0.0;
   out_4845788339544047954[37] = 0.0;
   out_4845788339544047954[38] = 0.0;
   out_4845788339544047954[39] = 0.0;
   out_4845788339544047954[40] = 1.0;
   out_4845788339544047954[41] = 0.0;
   out_4845788339544047954[42] = 0.0;
   out_4845788339544047954[43] = 0.0;
   out_4845788339544047954[44] = 0.0;
   out_4845788339544047954[45] = 0.0;
   out_4845788339544047954[46] = 0.0;
   out_4845788339544047954[47] = 0.0;
   out_4845788339544047954[48] = 0.0;
   out_4845788339544047954[49] = 0.0;
   out_4845788339544047954[50] = 1.0;
   out_4845788339544047954[51] = 0.0;
   out_4845788339544047954[52] = 0.0;
   out_4845788339544047954[53] = 0.0;
   out_4845788339544047954[54] = 0.0;
   out_4845788339544047954[55] = 0.0;
   out_4845788339544047954[56] = 0.0;
   out_4845788339544047954[57] = 0.0;
   out_4845788339544047954[58] = 0.0;
   out_4845788339544047954[59] = 0.0;
   out_4845788339544047954[60] = 1.0;
   out_4845788339544047954[61] = 0.0;
   out_4845788339544047954[62] = 0.0;
   out_4845788339544047954[63] = 0.0;
   out_4845788339544047954[64] = 0.0;
   out_4845788339544047954[65] = 0.0;
   out_4845788339544047954[66] = 0.0;
   out_4845788339544047954[67] = 0.0;
   out_4845788339544047954[68] = 0.0;
   out_4845788339544047954[69] = 0.0;
   out_4845788339544047954[70] = 1.0;
   out_4845788339544047954[71] = 0.0;
   out_4845788339544047954[72] = 0.0;
   out_4845788339544047954[73] = 0.0;
   out_4845788339544047954[74] = 0.0;
   out_4845788339544047954[75] = 0.0;
   out_4845788339544047954[76] = 0.0;
   out_4845788339544047954[77] = 0.0;
   out_4845788339544047954[78] = 0.0;
   out_4845788339544047954[79] = 0.0;
   out_4845788339544047954[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4185306989729419910) {
   out_4185306989729419910[0] = state[0];
   out_4185306989729419910[1] = state[1];
   out_4185306989729419910[2] = state[2];
   out_4185306989729419910[3] = state[3];
   out_4185306989729419910[4] = state[4];
   out_4185306989729419910[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4185306989729419910[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4185306989729419910[7] = state[7];
   out_4185306989729419910[8] = state[8];
}
void F_fun(double *state, double dt, double *out_8252178874365212967) {
   out_8252178874365212967[0] = 1;
   out_8252178874365212967[1] = 0;
   out_8252178874365212967[2] = 0;
   out_8252178874365212967[3] = 0;
   out_8252178874365212967[4] = 0;
   out_8252178874365212967[5] = 0;
   out_8252178874365212967[6] = 0;
   out_8252178874365212967[7] = 0;
   out_8252178874365212967[8] = 0;
   out_8252178874365212967[9] = 0;
   out_8252178874365212967[10] = 1;
   out_8252178874365212967[11] = 0;
   out_8252178874365212967[12] = 0;
   out_8252178874365212967[13] = 0;
   out_8252178874365212967[14] = 0;
   out_8252178874365212967[15] = 0;
   out_8252178874365212967[16] = 0;
   out_8252178874365212967[17] = 0;
   out_8252178874365212967[18] = 0;
   out_8252178874365212967[19] = 0;
   out_8252178874365212967[20] = 1;
   out_8252178874365212967[21] = 0;
   out_8252178874365212967[22] = 0;
   out_8252178874365212967[23] = 0;
   out_8252178874365212967[24] = 0;
   out_8252178874365212967[25] = 0;
   out_8252178874365212967[26] = 0;
   out_8252178874365212967[27] = 0;
   out_8252178874365212967[28] = 0;
   out_8252178874365212967[29] = 0;
   out_8252178874365212967[30] = 1;
   out_8252178874365212967[31] = 0;
   out_8252178874365212967[32] = 0;
   out_8252178874365212967[33] = 0;
   out_8252178874365212967[34] = 0;
   out_8252178874365212967[35] = 0;
   out_8252178874365212967[36] = 0;
   out_8252178874365212967[37] = 0;
   out_8252178874365212967[38] = 0;
   out_8252178874365212967[39] = 0;
   out_8252178874365212967[40] = 1;
   out_8252178874365212967[41] = 0;
   out_8252178874365212967[42] = 0;
   out_8252178874365212967[43] = 0;
   out_8252178874365212967[44] = 0;
   out_8252178874365212967[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_8252178874365212967[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_8252178874365212967[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8252178874365212967[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_8252178874365212967[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_8252178874365212967[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_8252178874365212967[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_8252178874365212967[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_8252178874365212967[53] = -9.8100000000000005*dt;
   out_8252178874365212967[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_8252178874365212967[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_8252178874365212967[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8252178874365212967[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8252178874365212967[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_8252178874365212967[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_8252178874365212967[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_8252178874365212967[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_8252178874365212967[62] = 0;
   out_8252178874365212967[63] = 0;
   out_8252178874365212967[64] = 0;
   out_8252178874365212967[65] = 0;
   out_8252178874365212967[66] = 0;
   out_8252178874365212967[67] = 0;
   out_8252178874365212967[68] = 0;
   out_8252178874365212967[69] = 0;
   out_8252178874365212967[70] = 1;
   out_8252178874365212967[71] = 0;
   out_8252178874365212967[72] = 0;
   out_8252178874365212967[73] = 0;
   out_8252178874365212967[74] = 0;
   out_8252178874365212967[75] = 0;
   out_8252178874365212967[76] = 0;
   out_8252178874365212967[77] = 0;
   out_8252178874365212967[78] = 0;
   out_8252178874365212967[79] = 0;
   out_8252178874365212967[80] = 1;
}
void h_25(double *state, double *unused, double *out_4739826667919645243) {
   out_4739826667919645243[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2698629402266667542) {
   out_2698629402266667542[0] = 0;
   out_2698629402266667542[1] = 0;
   out_2698629402266667542[2] = 0;
   out_2698629402266667542[3] = 0;
   out_2698629402266667542[4] = 0;
   out_2698629402266667542[5] = 0;
   out_2698629402266667542[6] = 1;
   out_2698629402266667542[7] = 0;
   out_2698629402266667542[8] = 0;
}
void h_24(double *state, double *unused, double *out_6091047700113278923) {
   out_6091047700113278923[0] = state[4];
   out_6091047700113278923[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2121692102389320721) {
   out_2121692102389320721[0] = 0;
   out_2121692102389320721[1] = 0;
   out_2121692102389320721[2] = 0;
   out_2121692102389320721[3] = 0;
   out_2121692102389320721[4] = 1;
   out_2121692102389320721[5] = 0;
   out_2121692102389320721[6] = 0;
   out_2121692102389320721[7] = 0;
   out_2121692102389320721[8] = 0;
   out_2121692102389320721[9] = 0;
   out_2121692102389320721[10] = 0;
   out_2121692102389320721[11] = 0;
   out_2121692102389320721[12] = 0;
   out_2121692102389320721[13] = 0;
   out_2121692102389320721[14] = 1;
   out_2121692102389320721[15] = 0;
   out_2121692102389320721[16] = 0;
   out_2121692102389320721[17] = 0;
}
void h_30(double *state, double *unused, double *out_7687552658275130204) {
   out_7687552658275130204[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2569290455123427472) {
   out_2569290455123427472[0] = 0;
   out_2569290455123427472[1] = 0;
   out_2569290455123427472[2] = 0;
   out_2569290455123427472[3] = 0;
   out_2569290455123427472[4] = 1;
   out_2569290455123427472[5] = 0;
   out_2569290455123427472[6] = 0;
   out_2569290455123427472[7] = 0;
   out_2569290455123427472[8] = 0;
}
void h_26(double *state, double *unused, double *out_7946639312164568029) {
   out_7946639312164568029[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1042873916607388682) {
   out_1042873916607388682[0] = 0;
   out_1042873916607388682[1] = 0;
   out_1042873916607388682[2] = 0;
   out_1042873916607388682[3] = 0;
   out_1042873916607388682[4] = 0;
   out_1042873916607388682[5] = 0;
   out_1042873916607388682[6] = 0;
   out_1042873916607388682[7] = 1;
   out_1042873916607388682[8] = 0;
}
void h_27(double *state, double *unused, double *out_3665830151724581410) {
   out_3665830151724581410[0] = state[3];
}
void H_27(double *state, double *unused, double *out_394527143323002561) {
   out_394527143323002561[0] = 0;
   out_394527143323002561[1] = 0;
   out_394527143323002561[2] = 0;
   out_394527143323002561[3] = 1;
   out_394527143323002561[4] = 0;
   out_394527143323002561[5] = 0;
   out_394527143323002561[6] = 0;
   out_394527143323002561[7] = 0;
   out_394527143323002561[8] = 0;
}
void h_29(double *state, double *unused, double *out_8290868542951607721) {
   out_8290868542951607721[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3079521799437819656) {
   out_3079521799437819656[0] = 0;
   out_3079521799437819656[1] = 1;
   out_3079521799437819656[2] = 0;
   out_3079521799437819656[3] = 0;
   out_3079521799437819656[4] = 0;
   out_3079521799437819656[5] = 0;
   out_3079521799437819656[6] = 0;
   out_3079521799437819656[7] = 0;
   out_3079521799437819656[8] = 0;
}
void h_28(double *state, double *unused, double *out_6846547824895893173) {
   out_6846547824895893173[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2002877217631710918) {
   out_2002877217631710918[0] = 1;
   out_2002877217631710918[1] = 0;
   out_2002877217631710918[2] = 0;
   out_2002877217631710918[3] = 0;
   out_2002877217631710918[4] = 0;
   out_2002877217631710918[5] = 0;
   out_2002877217631710918[6] = 0;
   out_2002877217631710918[7] = 0;
   out_2002877217631710918[8] = 0;
}
void h_31(double *state, double *unused, double *out_3141445982834403942) {
   out_3141445982834403942[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2729275364143627970) {
   out_2729275364143627970[0] = 0;
   out_2729275364143627970[1] = 0;
   out_2729275364143627970[2] = 0;
   out_2729275364143627970[3] = 0;
   out_2729275364143627970[4] = 0;
   out_2729275364143627970[5] = 0;
   out_2729275364143627970[6] = 0;
   out_2729275364143627970[7] = 0;
   out_2729275364143627970[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_1972702472511725479) {
  err_fun(nom_x, delta_x, out_1972702472511725479);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3741555659818717473) {
  inv_err_fun(nom_x, true_x, out_3741555659818717473);
}
void car_H_mod_fun(double *state, double *out_4845788339544047954) {
  H_mod_fun(state, out_4845788339544047954);
}
void car_f_fun(double *state, double dt, double *out_4185306989729419910) {
  f_fun(state,  dt, out_4185306989729419910);
}
void car_F_fun(double *state, double dt, double *out_8252178874365212967) {
  F_fun(state,  dt, out_8252178874365212967);
}
void car_h_25(double *state, double *unused, double *out_4739826667919645243) {
  h_25(state, unused, out_4739826667919645243);
}
void car_H_25(double *state, double *unused, double *out_2698629402266667542) {
  H_25(state, unused, out_2698629402266667542);
}
void car_h_24(double *state, double *unused, double *out_6091047700113278923) {
  h_24(state, unused, out_6091047700113278923);
}
void car_H_24(double *state, double *unused, double *out_2121692102389320721) {
  H_24(state, unused, out_2121692102389320721);
}
void car_h_30(double *state, double *unused, double *out_7687552658275130204) {
  h_30(state, unused, out_7687552658275130204);
}
void car_H_30(double *state, double *unused, double *out_2569290455123427472) {
  H_30(state, unused, out_2569290455123427472);
}
void car_h_26(double *state, double *unused, double *out_7946639312164568029) {
  h_26(state, unused, out_7946639312164568029);
}
void car_H_26(double *state, double *unused, double *out_1042873916607388682) {
  H_26(state, unused, out_1042873916607388682);
}
void car_h_27(double *state, double *unused, double *out_3665830151724581410) {
  h_27(state, unused, out_3665830151724581410);
}
void car_H_27(double *state, double *unused, double *out_394527143323002561) {
  H_27(state, unused, out_394527143323002561);
}
void car_h_29(double *state, double *unused, double *out_8290868542951607721) {
  h_29(state, unused, out_8290868542951607721);
}
void car_H_29(double *state, double *unused, double *out_3079521799437819656) {
  H_29(state, unused, out_3079521799437819656);
}
void car_h_28(double *state, double *unused, double *out_6846547824895893173) {
  h_28(state, unused, out_6846547824895893173);
}
void car_H_28(double *state, double *unused, double *out_2002877217631710918) {
  H_28(state, unused, out_2002877217631710918);
}
void car_h_31(double *state, double *unused, double *out_3141445982834403942) {
  h_31(state, unused, out_3141445982834403942);
}
void car_H_31(double *state, double *unused, double *out_2729275364143627970) {
  H_31(state, unused, out_2729275364143627970);
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
