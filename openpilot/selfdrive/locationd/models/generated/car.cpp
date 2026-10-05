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
void err_fun(double *nom_x, double *delta_x, double *out_7295323435102138985) {
   out_7295323435102138985[0] = delta_x[0] + nom_x[0];
   out_7295323435102138985[1] = delta_x[1] + nom_x[1];
   out_7295323435102138985[2] = delta_x[2] + nom_x[2];
   out_7295323435102138985[3] = delta_x[3] + nom_x[3];
   out_7295323435102138985[4] = delta_x[4] + nom_x[4];
   out_7295323435102138985[5] = delta_x[5] + nom_x[5];
   out_7295323435102138985[6] = delta_x[6] + nom_x[6];
   out_7295323435102138985[7] = delta_x[7] + nom_x[7];
   out_7295323435102138985[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5740214235924271464) {
   out_5740214235924271464[0] = -nom_x[0] + true_x[0];
   out_5740214235924271464[1] = -nom_x[1] + true_x[1];
   out_5740214235924271464[2] = -nom_x[2] + true_x[2];
   out_5740214235924271464[3] = -nom_x[3] + true_x[3];
   out_5740214235924271464[4] = -nom_x[4] + true_x[4];
   out_5740214235924271464[5] = -nom_x[5] + true_x[5];
   out_5740214235924271464[6] = -nom_x[6] + true_x[6];
   out_5740214235924271464[7] = -nom_x[7] + true_x[7];
   out_5740214235924271464[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_703782495897250555) {
   out_703782495897250555[0] = 1.0;
   out_703782495897250555[1] = 0.0;
   out_703782495897250555[2] = 0.0;
   out_703782495897250555[3] = 0.0;
   out_703782495897250555[4] = 0.0;
   out_703782495897250555[5] = 0.0;
   out_703782495897250555[6] = 0.0;
   out_703782495897250555[7] = 0.0;
   out_703782495897250555[8] = 0.0;
   out_703782495897250555[9] = 0.0;
   out_703782495897250555[10] = 1.0;
   out_703782495897250555[11] = 0.0;
   out_703782495897250555[12] = 0.0;
   out_703782495897250555[13] = 0.0;
   out_703782495897250555[14] = 0.0;
   out_703782495897250555[15] = 0.0;
   out_703782495897250555[16] = 0.0;
   out_703782495897250555[17] = 0.0;
   out_703782495897250555[18] = 0.0;
   out_703782495897250555[19] = 0.0;
   out_703782495897250555[20] = 1.0;
   out_703782495897250555[21] = 0.0;
   out_703782495897250555[22] = 0.0;
   out_703782495897250555[23] = 0.0;
   out_703782495897250555[24] = 0.0;
   out_703782495897250555[25] = 0.0;
   out_703782495897250555[26] = 0.0;
   out_703782495897250555[27] = 0.0;
   out_703782495897250555[28] = 0.0;
   out_703782495897250555[29] = 0.0;
   out_703782495897250555[30] = 1.0;
   out_703782495897250555[31] = 0.0;
   out_703782495897250555[32] = 0.0;
   out_703782495897250555[33] = 0.0;
   out_703782495897250555[34] = 0.0;
   out_703782495897250555[35] = 0.0;
   out_703782495897250555[36] = 0.0;
   out_703782495897250555[37] = 0.0;
   out_703782495897250555[38] = 0.0;
   out_703782495897250555[39] = 0.0;
   out_703782495897250555[40] = 1.0;
   out_703782495897250555[41] = 0.0;
   out_703782495897250555[42] = 0.0;
   out_703782495897250555[43] = 0.0;
   out_703782495897250555[44] = 0.0;
   out_703782495897250555[45] = 0.0;
   out_703782495897250555[46] = 0.0;
   out_703782495897250555[47] = 0.0;
   out_703782495897250555[48] = 0.0;
   out_703782495897250555[49] = 0.0;
   out_703782495897250555[50] = 1.0;
   out_703782495897250555[51] = 0.0;
   out_703782495897250555[52] = 0.0;
   out_703782495897250555[53] = 0.0;
   out_703782495897250555[54] = 0.0;
   out_703782495897250555[55] = 0.0;
   out_703782495897250555[56] = 0.0;
   out_703782495897250555[57] = 0.0;
   out_703782495897250555[58] = 0.0;
   out_703782495897250555[59] = 0.0;
   out_703782495897250555[60] = 1.0;
   out_703782495897250555[61] = 0.0;
   out_703782495897250555[62] = 0.0;
   out_703782495897250555[63] = 0.0;
   out_703782495897250555[64] = 0.0;
   out_703782495897250555[65] = 0.0;
   out_703782495897250555[66] = 0.0;
   out_703782495897250555[67] = 0.0;
   out_703782495897250555[68] = 0.0;
   out_703782495897250555[69] = 0.0;
   out_703782495897250555[70] = 1.0;
   out_703782495897250555[71] = 0.0;
   out_703782495897250555[72] = 0.0;
   out_703782495897250555[73] = 0.0;
   out_703782495897250555[74] = 0.0;
   out_703782495897250555[75] = 0.0;
   out_703782495897250555[76] = 0.0;
   out_703782495897250555[77] = 0.0;
   out_703782495897250555[78] = 0.0;
   out_703782495897250555[79] = 0.0;
   out_703782495897250555[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4026170021074555431) {
   out_4026170021074555431[0] = state[0];
   out_4026170021074555431[1] = state[1];
   out_4026170021074555431[2] = state[2];
   out_4026170021074555431[3] = state[3];
   out_4026170021074555431[4] = state[4];
   out_4026170021074555431[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4026170021074555431[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4026170021074555431[7] = state[7];
   out_4026170021074555431[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4652814377482513796) {
   out_4652814377482513796[0] = 1;
   out_4652814377482513796[1] = 0;
   out_4652814377482513796[2] = 0;
   out_4652814377482513796[3] = 0;
   out_4652814377482513796[4] = 0;
   out_4652814377482513796[5] = 0;
   out_4652814377482513796[6] = 0;
   out_4652814377482513796[7] = 0;
   out_4652814377482513796[8] = 0;
   out_4652814377482513796[9] = 0;
   out_4652814377482513796[10] = 1;
   out_4652814377482513796[11] = 0;
   out_4652814377482513796[12] = 0;
   out_4652814377482513796[13] = 0;
   out_4652814377482513796[14] = 0;
   out_4652814377482513796[15] = 0;
   out_4652814377482513796[16] = 0;
   out_4652814377482513796[17] = 0;
   out_4652814377482513796[18] = 0;
   out_4652814377482513796[19] = 0;
   out_4652814377482513796[20] = 1;
   out_4652814377482513796[21] = 0;
   out_4652814377482513796[22] = 0;
   out_4652814377482513796[23] = 0;
   out_4652814377482513796[24] = 0;
   out_4652814377482513796[25] = 0;
   out_4652814377482513796[26] = 0;
   out_4652814377482513796[27] = 0;
   out_4652814377482513796[28] = 0;
   out_4652814377482513796[29] = 0;
   out_4652814377482513796[30] = 1;
   out_4652814377482513796[31] = 0;
   out_4652814377482513796[32] = 0;
   out_4652814377482513796[33] = 0;
   out_4652814377482513796[34] = 0;
   out_4652814377482513796[35] = 0;
   out_4652814377482513796[36] = 0;
   out_4652814377482513796[37] = 0;
   out_4652814377482513796[38] = 0;
   out_4652814377482513796[39] = 0;
   out_4652814377482513796[40] = 1;
   out_4652814377482513796[41] = 0;
   out_4652814377482513796[42] = 0;
   out_4652814377482513796[43] = 0;
   out_4652814377482513796[44] = 0;
   out_4652814377482513796[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4652814377482513796[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4652814377482513796[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4652814377482513796[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4652814377482513796[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4652814377482513796[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4652814377482513796[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4652814377482513796[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4652814377482513796[53] = -9.8100000000000005*dt;
   out_4652814377482513796[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4652814377482513796[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4652814377482513796[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4652814377482513796[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4652814377482513796[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4652814377482513796[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4652814377482513796[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4652814377482513796[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4652814377482513796[62] = 0;
   out_4652814377482513796[63] = 0;
   out_4652814377482513796[64] = 0;
   out_4652814377482513796[65] = 0;
   out_4652814377482513796[66] = 0;
   out_4652814377482513796[67] = 0;
   out_4652814377482513796[68] = 0;
   out_4652814377482513796[69] = 0;
   out_4652814377482513796[70] = 1;
   out_4652814377482513796[71] = 0;
   out_4652814377482513796[72] = 0;
   out_4652814377482513796[73] = 0;
   out_4652814377482513796[74] = 0;
   out_4652814377482513796[75] = 0;
   out_4652814377482513796[76] = 0;
   out_4652814377482513796[77] = 0;
   out_4652814377482513796[78] = 0;
   out_4652814377482513796[79] = 0;
   out_4652814377482513796[80] = 1;
}
void h_25(double *state, double *unused, double *out_4039743270013067154) {
   out_4039743270013067154[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4226763145886742232) {
   out_4226763145886742232[0] = 0;
   out_4226763145886742232[1] = 0;
   out_4226763145886742232[2] = 0;
   out_4226763145886742232[3] = 0;
   out_4226763145886742232[4] = 0;
   out_4226763145886742232[5] = 0;
   out_4226763145886742232[6] = 1;
   out_4226763145886742232[7] = 0;
   out_4226763145886742232[8] = 0;
}
void h_24(double *state, double *unused, double *out_3606421098967363994) {
   out_3606421098967363994[0] = state[4];
   out_3606421098967363994[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6403977569493892205) {
   out_6403977569493892205[0] = 0;
   out_6403977569493892205[1] = 0;
   out_6403977569493892205[2] = 0;
   out_6403977569493892205[3] = 0;
   out_6403977569493892205[4] = 1;
   out_6403977569493892205[5] = 0;
   out_6403977569493892205[6] = 0;
   out_6403977569493892205[7] = 0;
   out_6403977569493892205[8] = 0;
   out_6403977569493892205[9] = 0;
   out_6403977569493892205[10] = 0;
   out_6403977569493892205[11] = 0;
   out_6403977569493892205[12] = 0;
   out_6403977569493892205[13] = 0;
   out_6403977569493892205[14] = 1;
   out_6403977569493892205[15] = 0;
   out_6403977569493892205[16] = 0;
   out_6403977569493892205[17] = 0;
}
void h_30(double *state, double *unused, double *out_4600134206705474730) {
   out_4600134206705474730[0] = state[4];
}
void H_30(double *state, double *unused, double *out_6745096104393990859) {
   out_6745096104393990859[0] = 0;
   out_6745096104393990859[1] = 0;
   out_6745096104393990859[2] = 0;
   out_6745096104393990859[3] = 0;
   out_6745096104393990859[4] = 1;
   out_6745096104393990859[5] = 0;
   out_6745096104393990859[6] = 0;
   out_6745096104393990859[7] = 0;
   out_6745096104393990859[8] = 0;
}
void h_26(double *state, double *unused, double *out_1787582103435621347) {
   out_1787582103435621347[0] = state[7];
}
void H_26(double *state, double *unused, double *out_485259827012686008) {
   out_485259827012686008[0] = 0;
   out_485259827012686008[1] = 0;
   out_485259827012686008[2] = 0;
   out_485259827012686008[3] = 0;
   out_485259827012686008[4] = 0;
   out_485259827012686008[5] = 0;
   out_485259827012686008[6] = 0;
   out_485259827012686008[7] = 1;
   out_485259827012686008[8] = 0;
}
void h_27(double *state, double *unused, double *out_9041416537673912799) {
   out_9041416537673912799[0] = state[3];
}
void H_27(double *state, double *unused, double *out_8968690175577934076) {
   out_8968690175577934076[0] = 0;
   out_8968690175577934076[1] = 0;
   out_8968690175577934076[2] = 0;
   out_8968690175577934076[3] = 1;
   out_8968690175577934076[4] = 0;
   out_8968690175577934076[5] = 0;
   out_8968690175577934076[6] = 0;
   out_8968690175577934076[7] = 0;
   out_8968690175577934076[8] = 0;
}
void h_29(double *state, double *unused, double *out_5767878007781616467) {
   out_5767878007781616467[0] = state[1];
}
void H_29(double *state, double *unused, double *out_7255327448708383043) {
   out_7255327448708383043[0] = 0;
   out_7255327448708383043[1] = 1;
   out_7255327448708383043[2] = 0;
   out_7255327448708383043[3] = 0;
   out_7255327448708383043[4] = 0;
   out_7255327448708383043[5] = 0;
   out_7255327448708383043[6] = 0;
   out_7255327448708383043[7] = 0;
   out_7255327448708383043[8] = 0;
}
void h_28(double *state, double *unused, double *out_5400909299850363481) {
   out_5400909299850363481[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2172928431638852469) {
   out_2172928431638852469[0] = 1;
   out_2172928431638852469[1] = 0;
   out_2172928431638852469[2] = 0;
   out_2172928431638852469[3] = 0;
   out_2172928431638852469[4] = 0;
   out_2172928431638852469[5] = 0;
   out_2172928431638852469[6] = 0;
   out_2172928431638852469[7] = 0;
   out_2172928431638852469[8] = 0;
}
void h_31(double *state, double *unused, double *out_3764549207728561265) {
   out_3764549207728561265[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4257409107763702660) {
   out_4257409107763702660[0] = 0;
   out_4257409107763702660[1] = 0;
   out_4257409107763702660[2] = 0;
   out_4257409107763702660[3] = 0;
   out_4257409107763702660[4] = 0;
   out_4257409107763702660[5] = 0;
   out_4257409107763702660[6] = 0;
   out_4257409107763702660[7] = 0;
   out_4257409107763702660[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_7295323435102138985) {
  err_fun(nom_x, delta_x, out_7295323435102138985);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5740214235924271464) {
  inv_err_fun(nom_x, true_x, out_5740214235924271464);
}
void car_H_mod_fun(double *state, double *out_703782495897250555) {
  H_mod_fun(state, out_703782495897250555);
}
void car_f_fun(double *state, double dt, double *out_4026170021074555431) {
  f_fun(state,  dt, out_4026170021074555431);
}
void car_F_fun(double *state, double dt, double *out_4652814377482513796) {
  F_fun(state,  dt, out_4652814377482513796);
}
void car_h_25(double *state, double *unused, double *out_4039743270013067154) {
  h_25(state, unused, out_4039743270013067154);
}
void car_H_25(double *state, double *unused, double *out_4226763145886742232) {
  H_25(state, unused, out_4226763145886742232);
}
void car_h_24(double *state, double *unused, double *out_3606421098967363994) {
  h_24(state, unused, out_3606421098967363994);
}
void car_H_24(double *state, double *unused, double *out_6403977569493892205) {
  H_24(state, unused, out_6403977569493892205);
}
void car_h_30(double *state, double *unused, double *out_4600134206705474730) {
  h_30(state, unused, out_4600134206705474730);
}
void car_H_30(double *state, double *unused, double *out_6745096104393990859) {
  H_30(state, unused, out_6745096104393990859);
}
void car_h_26(double *state, double *unused, double *out_1787582103435621347) {
  h_26(state, unused, out_1787582103435621347);
}
void car_H_26(double *state, double *unused, double *out_485259827012686008) {
  H_26(state, unused, out_485259827012686008);
}
void car_h_27(double *state, double *unused, double *out_9041416537673912799) {
  h_27(state, unused, out_9041416537673912799);
}
void car_H_27(double *state, double *unused, double *out_8968690175577934076) {
  H_27(state, unused, out_8968690175577934076);
}
void car_h_29(double *state, double *unused, double *out_5767878007781616467) {
  h_29(state, unused, out_5767878007781616467);
}
void car_H_29(double *state, double *unused, double *out_7255327448708383043) {
  H_29(state, unused, out_7255327448708383043);
}
void car_h_28(double *state, double *unused, double *out_5400909299850363481) {
  h_28(state, unused, out_5400909299850363481);
}
void car_H_28(double *state, double *unused, double *out_2172928431638852469) {
  H_28(state, unused, out_2172928431638852469);
}
void car_h_31(double *state, double *unused, double *out_3764549207728561265) {
  h_31(state, unused, out_3764549207728561265);
}
void car_H_31(double *state, double *unused, double *out_4257409107763702660) {
  H_31(state, unused, out_4257409107763702660);
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
