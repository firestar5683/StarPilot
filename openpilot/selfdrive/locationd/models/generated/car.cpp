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
void err_fun(double *nom_x, double *delta_x, double *out_2228678220985197488) {
   out_2228678220985197488[0] = delta_x[0] + nom_x[0];
   out_2228678220985197488[1] = delta_x[1] + nom_x[1];
   out_2228678220985197488[2] = delta_x[2] + nom_x[2];
   out_2228678220985197488[3] = delta_x[3] + nom_x[3];
   out_2228678220985197488[4] = delta_x[4] + nom_x[4];
   out_2228678220985197488[5] = delta_x[5] + nom_x[5];
   out_2228678220985197488[6] = delta_x[6] + nom_x[6];
   out_2228678220985197488[7] = delta_x[7] + nom_x[7];
   out_2228678220985197488[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_4771042334963074054) {
   out_4771042334963074054[0] = -nom_x[0] + true_x[0];
   out_4771042334963074054[1] = -nom_x[1] + true_x[1];
   out_4771042334963074054[2] = -nom_x[2] + true_x[2];
   out_4771042334963074054[3] = -nom_x[3] + true_x[3];
   out_4771042334963074054[4] = -nom_x[4] + true_x[4];
   out_4771042334963074054[5] = -nom_x[5] + true_x[5];
   out_4771042334963074054[6] = -nom_x[6] + true_x[6];
   out_4771042334963074054[7] = -nom_x[7] + true_x[7];
   out_4771042334963074054[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_6842308674734904229) {
   out_6842308674734904229[0] = 1.0;
   out_6842308674734904229[1] = 0.0;
   out_6842308674734904229[2] = 0.0;
   out_6842308674734904229[3] = 0.0;
   out_6842308674734904229[4] = 0.0;
   out_6842308674734904229[5] = 0.0;
   out_6842308674734904229[6] = 0.0;
   out_6842308674734904229[7] = 0.0;
   out_6842308674734904229[8] = 0.0;
   out_6842308674734904229[9] = 0.0;
   out_6842308674734904229[10] = 1.0;
   out_6842308674734904229[11] = 0.0;
   out_6842308674734904229[12] = 0.0;
   out_6842308674734904229[13] = 0.0;
   out_6842308674734904229[14] = 0.0;
   out_6842308674734904229[15] = 0.0;
   out_6842308674734904229[16] = 0.0;
   out_6842308674734904229[17] = 0.0;
   out_6842308674734904229[18] = 0.0;
   out_6842308674734904229[19] = 0.0;
   out_6842308674734904229[20] = 1.0;
   out_6842308674734904229[21] = 0.0;
   out_6842308674734904229[22] = 0.0;
   out_6842308674734904229[23] = 0.0;
   out_6842308674734904229[24] = 0.0;
   out_6842308674734904229[25] = 0.0;
   out_6842308674734904229[26] = 0.0;
   out_6842308674734904229[27] = 0.0;
   out_6842308674734904229[28] = 0.0;
   out_6842308674734904229[29] = 0.0;
   out_6842308674734904229[30] = 1.0;
   out_6842308674734904229[31] = 0.0;
   out_6842308674734904229[32] = 0.0;
   out_6842308674734904229[33] = 0.0;
   out_6842308674734904229[34] = 0.0;
   out_6842308674734904229[35] = 0.0;
   out_6842308674734904229[36] = 0.0;
   out_6842308674734904229[37] = 0.0;
   out_6842308674734904229[38] = 0.0;
   out_6842308674734904229[39] = 0.0;
   out_6842308674734904229[40] = 1.0;
   out_6842308674734904229[41] = 0.0;
   out_6842308674734904229[42] = 0.0;
   out_6842308674734904229[43] = 0.0;
   out_6842308674734904229[44] = 0.0;
   out_6842308674734904229[45] = 0.0;
   out_6842308674734904229[46] = 0.0;
   out_6842308674734904229[47] = 0.0;
   out_6842308674734904229[48] = 0.0;
   out_6842308674734904229[49] = 0.0;
   out_6842308674734904229[50] = 1.0;
   out_6842308674734904229[51] = 0.0;
   out_6842308674734904229[52] = 0.0;
   out_6842308674734904229[53] = 0.0;
   out_6842308674734904229[54] = 0.0;
   out_6842308674734904229[55] = 0.0;
   out_6842308674734904229[56] = 0.0;
   out_6842308674734904229[57] = 0.0;
   out_6842308674734904229[58] = 0.0;
   out_6842308674734904229[59] = 0.0;
   out_6842308674734904229[60] = 1.0;
   out_6842308674734904229[61] = 0.0;
   out_6842308674734904229[62] = 0.0;
   out_6842308674734904229[63] = 0.0;
   out_6842308674734904229[64] = 0.0;
   out_6842308674734904229[65] = 0.0;
   out_6842308674734904229[66] = 0.0;
   out_6842308674734904229[67] = 0.0;
   out_6842308674734904229[68] = 0.0;
   out_6842308674734904229[69] = 0.0;
   out_6842308674734904229[70] = 1.0;
   out_6842308674734904229[71] = 0.0;
   out_6842308674734904229[72] = 0.0;
   out_6842308674734904229[73] = 0.0;
   out_6842308674734904229[74] = 0.0;
   out_6842308674734904229[75] = 0.0;
   out_6842308674734904229[76] = 0.0;
   out_6842308674734904229[77] = 0.0;
   out_6842308674734904229[78] = 0.0;
   out_6842308674734904229[79] = 0.0;
   out_6842308674734904229[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_5170868391674818667) {
   out_5170868391674818667[0] = state[0];
   out_5170868391674818667[1] = state[1];
   out_5170868391674818667[2] = state[2];
   out_5170868391674818667[3] = state[3];
   out_5170868391674818667[4] = state[4];
   out_5170868391674818667[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_5170868391674818667[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_5170868391674818667[7] = state[7];
   out_5170868391674818667[8] = state[8];
}
void F_fun(double *state, double dt, double *out_608002520374966168) {
   out_608002520374966168[0] = 1;
   out_608002520374966168[1] = 0;
   out_608002520374966168[2] = 0;
   out_608002520374966168[3] = 0;
   out_608002520374966168[4] = 0;
   out_608002520374966168[5] = 0;
   out_608002520374966168[6] = 0;
   out_608002520374966168[7] = 0;
   out_608002520374966168[8] = 0;
   out_608002520374966168[9] = 0;
   out_608002520374966168[10] = 1;
   out_608002520374966168[11] = 0;
   out_608002520374966168[12] = 0;
   out_608002520374966168[13] = 0;
   out_608002520374966168[14] = 0;
   out_608002520374966168[15] = 0;
   out_608002520374966168[16] = 0;
   out_608002520374966168[17] = 0;
   out_608002520374966168[18] = 0;
   out_608002520374966168[19] = 0;
   out_608002520374966168[20] = 1;
   out_608002520374966168[21] = 0;
   out_608002520374966168[22] = 0;
   out_608002520374966168[23] = 0;
   out_608002520374966168[24] = 0;
   out_608002520374966168[25] = 0;
   out_608002520374966168[26] = 0;
   out_608002520374966168[27] = 0;
   out_608002520374966168[28] = 0;
   out_608002520374966168[29] = 0;
   out_608002520374966168[30] = 1;
   out_608002520374966168[31] = 0;
   out_608002520374966168[32] = 0;
   out_608002520374966168[33] = 0;
   out_608002520374966168[34] = 0;
   out_608002520374966168[35] = 0;
   out_608002520374966168[36] = 0;
   out_608002520374966168[37] = 0;
   out_608002520374966168[38] = 0;
   out_608002520374966168[39] = 0;
   out_608002520374966168[40] = 1;
   out_608002520374966168[41] = 0;
   out_608002520374966168[42] = 0;
   out_608002520374966168[43] = 0;
   out_608002520374966168[44] = 0;
   out_608002520374966168[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_608002520374966168[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_608002520374966168[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_608002520374966168[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_608002520374966168[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_608002520374966168[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_608002520374966168[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_608002520374966168[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_608002520374966168[53] = -9.8100000000000005*dt;
   out_608002520374966168[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_608002520374966168[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_608002520374966168[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_608002520374966168[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_608002520374966168[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_608002520374966168[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_608002520374966168[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_608002520374966168[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_608002520374966168[62] = 0;
   out_608002520374966168[63] = 0;
   out_608002520374966168[64] = 0;
   out_608002520374966168[65] = 0;
   out_608002520374966168[66] = 0;
   out_608002520374966168[67] = 0;
   out_608002520374966168[68] = 0;
   out_608002520374966168[69] = 0;
   out_608002520374966168[70] = 1;
   out_608002520374966168[71] = 0;
   out_608002520374966168[72] = 0;
   out_608002520374966168[73] = 0;
   out_608002520374966168[74] = 0;
   out_608002520374966168[75] = 0;
   out_608002520374966168[76] = 0;
   out_608002520374966168[77] = 0;
   out_608002520374966168[78] = 0;
   out_608002520374966168[79] = 0;
   out_608002520374966168[80] = 1;
}
void h_25(double *state, double *unused, double *out_5717488514750397721) {
   out_5717488514750397721[0] = state[6];
}
void H_25(double *state, double *unused, double *out_2411247173062410150) {
   out_2411247173062410150[0] = 0;
   out_2411247173062410150[1] = 0;
   out_2411247173062410150[2] = 0;
   out_2411247173062410150[3] = 0;
   out_2411247173062410150[4] = 0;
   out_2411247173062410150[5] = 0;
   out_2411247173062410150[6] = 1;
   out_2411247173062410150[7] = 0;
   out_2411247173062410150[8] = 0;
}
void h_24(double *state, double *unused, double *out_3636388376143156521) {
   out_3636388376143156521[0] = state[4];
   out_3636388376143156521[1] = state[5];
}
void H_24(double *state, double *unused, double *out_4636954957041278712) {
   out_4636954957041278712[0] = 0;
   out_4636954957041278712[1] = 0;
   out_4636954957041278712[2] = 0;
   out_4636954957041278712[3] = 0;
   out_4636954957041278712[4] = 1;
   out_4636954957041278712[5] = 0;
   out_4636954957041278712[6] = 0;
   out_4636954957041278712[7] = 0;
   out_4636954957041278712[8] = 0;
   out_4636954957041278712[9] = 0;
   out_4636954957041278712[10] = 0;
   out_4636954957041278712[11] = 0;
   out_4636954957041278712[12] = 0;
   out_4636954957041278712[13] = 0;
   out_4636954957041278712[14] = 1;
   out_4636954957041278712[15] = 0;
   out_4636954957041278712[16] = 0;
   out_4636954957041278712[17] = 0;
}
void h_30(double *state, double *unused, double *out_1053346711599953215) {
   out_1053346711599953215[0] = state[4];
}
void H_30(double *state, double *unused, double *out_9118806559155524711) {
   out_9118806559155524711[0] = 0;
   out_9118806559155524711[1] = 0;
   out_9118806559155524711[2] = 0;
   out_9118806559155524711[3] = 0;
   out_9118806559155524711[4] = 1;
   out_9118806559155524711[5] = 0;
   out_9118806559155524711[6] = 0;
   out_9118806559155524711[7] = 0;
   out_9118806559155524711[8] = 0;
}
void h_26(double *state, double *unused, double *out_6055019979260798860) {
   out_6055019979260798860[0] = state[7];
}
void H_26(double *state, double *unused, double *out_1330256145811646074) {
   out_1330256145811646074[0] = 0;
   out_1330256145811646074[1] = 0;
   out_1330256145811646074[2] = 0;
   out_1330256145811646074[3] = 0;
   out_1330256145811646074[4] = 0;
   out_1330256145811646074[5] = 0;
   out_1330256145811646074[6] = 0;
   out_1330256145811646074[7] = 1;
   out_1330256145811646074[8] = 0;
}
void h_27(double *state, double *unused, double *out_8107069529503045581) {
   out_8107069529503045581[0] = state[3];
}
void H_27(double *state, double *unused, double *out_7153174202753601994) {
   out_7153174202753601994[0] = 0;
   out_7153174202753601994[1] = 0;
   out_7153174202753601994[2] = 0;
   out_7153174202753601994[3] = 1;
   out_7153174202753601994[4] = 0;
   out_7153174202753601994[5] = 0;
   out_7153174202753601994[6] = 0;
   out_7153174202753601994[7] = 0;
   out_7153174202753601994[8] = 0;
}
void h_29(double *state, double *unused, double *out_3948326556060892430) {
   out_3948326556060892430[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8608575214841132527) {
   out_8608575214841132527[0] = 0;
   out_8608575214841132527[1] = 1;
   out_8608575214841132527[2] = 0;
   out_8608575214841132527[3] = 0;
   out_8608575214841132527[4] = 0;
   out_8608575214841132527[5] = 0;
   out_8608575214841132527[6] = 0;
   out_8608575214841132527[7] = 0;
   out_8608575214841132527[8] = 0;
}
void h_28(double *state, double *unused, double *out_9171930743130364298) {
   out_9171930743130364298[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4755769841798888515) {
   out_4755769841798888515[0] = 1;
   out_4755769841798888515[1] = 0;
   out_4755769841798888515[2] = 0;
   out_4755769841798888515[3] = 0;
   out_4755769841798888515[4] = 0;
   out_4755769841798888515[5] = 0;
   out_4755769841798888515[6] = 0;
   out_4755769841798888515[7] = 0;
   out_4755769841798888515[8] = 0;
}
void h_31(double *state, double *unused, double *out_5874675183101526866) {
   out_5874675183101526866[0] = state[8];
}
void H_31(double *state, double *unused, double *out_2441893134939370578) {
   out_2441893134939370578[0] = 0;
   out_2441893134939370578[1] = 0;
   out_2441893134939370578[2] = 0;
   out_2441893134939370578[3] = 0;
   out_2441893134939370578[4] = 0;
   out_2441893134939370578[5] = 0;
   out_2441893134939370578[6] = 0;
   out_2441893134939370578[7] = 0;
   out_2441893134939370578[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_2228678220985197488) {
  err_fun(nom_x, delta_x, out_2228678220985197488);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_4771042334963074054) {
  inv_err_fun(nom_x, true_x, out_4771042334963074054);
}
void car_H_mod_fun(double *state, double *out_6842308674734904229) {
  H_mod_fun(state, out_6842308674734904229);
}
void car_f_fun(double *state, double dt, double *out_5170868391674818667) {
  f_fun(state,  dt, out_5170868391674818667);
}
void car_F_fun(double *state, double dt, double *out_608002520374966168) {
  F_fun(state,  dt, out_608002520374966168);
}
void car_h_25(double *state, double *unused, double *out_5717488514750397721) {
  h_25(state, unused, out_5717488514750397721);
}
void car_H_25(double *state, double *unused, double *out_2411247173062410150) {
  H_25(state, unused, out_2411247173062410150);
}
void car_h_24(double *state, double *unused, double *out_3636388376143156521) {
  h_24(state, unused, out_3636388376143156521);
}
void car_H_24(double *state, double *unused, double *out_4636954957041278712) {
  H_24(state, unused, out_4636954957041278712);
}
void car_h_30(double *state, double *unused, double *out_1053346711599953215) {
  h_30(state, unused, out_1053346711599953215);
}
void car_H_30(double *state, double *unused, double *out_9118806559155524711) {
  H_30(state, unused, out_9118806559155524711);
}
void car_h_26(double *state, double *unused, double *out_6055019979260798860) {
  h_26(state, unused, out_6055019979260798860);
}
void car_H_26(double *state, double *unused, double *out_1330256145811646074) {
  H_26(state, unused, out_1330256145811646074);
}
void car_h_27(double *state, double *unused, double *out_8107069529503045581) {
  h_27(state, unused, out_8107069529503045581);
}
void car_H_27(double *state, double *unused, double *out_7153174202753601994) {
  H_27(state, unused, out_7153174202753601994);
}
void car_h_29(double *state, double *unused, double *out_3948326556060892430) {
  h_29(state, unused, out_3948326556060892430);
}
void car_H_29(double *state, double *unused, double *out_8608575214841132527) {
  H_29(state, unused, out_8608575214841132527);
}
void car_h_28(double *state, double *unused, double *out_9171930743130364298) {
  h_28(state, unused, out_9171930743130364298);
}
void car_H_28(double *state, double *unused, double *out_4755769841798888515) {
  H_28(state, unused, out_4755769841798888515);
}
void car_h_31(double *state, double *unused, double *out_5874675183101526866) {
  h_31(state, unused, out_5874675183101526866);
}
void car_H_31(double *state, double *unused, double *out_2441893134939370578) {
  H_31(state, unused, out_2441893134939370578);
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
