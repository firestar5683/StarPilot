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
void err_fun(double *nom_x, double *delta_x, double *out_949748206832459961) {
   out_949748206832459961[0] = delta_x[0] + nom_x[0];
   out_949748206832459961[1] = delta_x[1] + nom_x[1];
   out_949748206832459961[2] = delta_x[2] + nom_x[2];
   out_949748206832459961[3] = delta_x[3] + nom_x[3];
   out_949748206832459961[4] = delta_x[4] + nom_x[4];
   out_949748206832459961[5] = delta_x[5] + nom_x[5];
   out_949748206832459961[6] = delta_x[6] + nom_x[6];
   out_949748206832459961[7] = delta_x[7] + nom_x[7];
   out_949748206832459961[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3637275118739236570) {
   out_3637275118739236570[0] = -nom_x[0] + true_x[0];
   out_3637275118739236570[1] = -nom_x[1] + true_x[1];
   out_3637275118739236570[2] = -nom_x[2] + true_x[2];
   out_3637275118739236570[3] = -nom_x[3] + true_x[3];
   out_3637275118739236570[4] = -nom_x[4] + true_x[4];
   out_3637275118739236570[5] = -nom_x[5] + true_x[5];
   out_3637275118739236570[6] = -nom_x[6] + true_x[6];
   out_3637275118739236570[7] = -nom_x[7] + true_x[7];
   out_3637275118739236570[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2022350626202111920) {
   out_2022350626202111920[0] = 1.0;
   out_2022350626202111920[1] = 0.0;
   out_2022350626202111920[2] = 0.0;
   out_2022350626202111920[3] = 0.0;
   out_2022350626202111920[4] = 0.0;
   out_2022350626202111920[5] = 0.0;
   out_2022350626202111920[6] = 0.0;
   out_2022350626202111920[7] = 0.0;
   out_2022350626202111920[8] = 0.0;
   out_2022350626202111920[9] = 0.0;
   out_2022350626202111920[10] = 1.0;
   out_2022350626202111920[11] = 0.0;
   out_2022350626202111920[12] = 0.0;
   out_2022350626202111920[13] = 0.0;
   out_2022350626202111920[14] = 0.0;
   out_2022350626202111920[15] = 0.0;
   out_2022350626202111920[16] = 0.0;
   out_2022350626202111920[17] = 0.0;
   out_2022350626202111920[18] = 0.0;
   out_2022350626202111920[19] = 0.0;
   out_2022350626202111920[20] = 1.0;
   out_2022350626202111920[21] = 0.0;
   out_2022350626202111920[22] = 0.0;
   out_2022350626202111920[23] = 0.0;
   out_2022350626202111920[24] = 0.0;
   out_2022350626202111920[25] = 0.0;
   out_2022350626202111920[26] = 0.0;
   out_2022350626202111920[27] = 0.0;
   out_2022350626202111920[28] = 0.0;
   out_2022350626202111920[29] = 0.0;
   out_2022350626202111920[30] = 1.0;
   out_2022350626202111920[31] = 0.0;
   out_2022350626202111920[32] = 0.0;
   out_2022350626202111920[33] = 0.0;
   out_2022350626202111920[34] = 0.0;
   out_2022350626202111920[35] = 0.0;
   out_2022350626202111920[36] = 0.0;
   out_2022350626202111920[37] = 0.0;
   out_2022350626202111920[38] = 0.0;
   out_2022350626202111920[39] = 0.0;
   out_2022350626202111920[40] = 1.0;
   out_2022350626202111920[41] = 0.0;
   out_2022350626202111920[42] = 0.0;
   out_2022350626202111920[43] = 0.0;
   out_2022350626202111920[44] = 0.0;
   out_2022350626202111920[45] = 0.0;
   out_2022350626202111920[46] = 0.0;
   out_2022350626202111920[47] = 0.0;
   out_2022350626202111920[48] = 0.0;
   out_2022350626202111920[49] = 0.0;
   out_2022350626202111920[50] = 1.0;
   out_2022350626202111920[51] = 0.0;
   out_2022350626202111920[52] = 0.0;
   out_2022350626202111920[53] = 0.0;
   out_2022350626202111920[54] = 0.0;
   out_2022350626202111920[55] = 0.0;
   out_2022350626202111920[56] = 0.0;
   out_2022350626202111920[57] = 0.0;
   out_2022350626202111920[58] = 0.0;
   out_2022350626202111920[59] = 0.0;
   out_2022350626202111920[60] = 1.0;
   out_2022350626202111920[61] = 0.0;
   out_2022350626202111920[62] = 0.0;
   out_2022350626202111920[63] = 0.0;
   out_2022350626202111920[64] = 0.0;
   out_2022350626202111920[65] = 0.0;
   out_2022350626202111920[66] = 0.0;
   out_2022350626202111920[67] = 0.0;
   out_2022350626202111920[68] = 0.0;
   out_2022350626202111920[69] = 0.0;
   out_2022350626202111920[70] = 1.0;
   out_2022350626202111920[71] = 0.0;
   out_2022350626202111920[72] = 0.0;
   out_2022350626202111920[73] = 0.0;
   out_2022350626202111920[74] = 0.0;
   out_2022350626202111920[75] = 0.0;
   out_2022350626202111920[76] = 0.0;
   out_2022350626202111920[77] = 0.0;
   out_2022350626202111920[78] = 0.0;
   out_2022350626202111920[79] = 0.0;
   out_2022350626202111920[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_311349171040061963) {
   out_311349171040061963[0] = state[0];
   out_311349171040061963[1] = state[1];
   out_311349171040061963[2] = state[2];
   out_311349171040061963[3] = state[3];
   out_311349171040061963[4] = state[4];
   out_311349171040061963[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_311349171040061963[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_311349171040061963[7] = state[7];
   out_311349171040061963[8] = state[8];
}
void F_fun(double *state, double dt, double *out_7710363422868589643) {
   out_7710363422868589643[0] = 1;
   out_7710363422868589643[1] = 0;
   out_7710363422868589643[2] = 0;
   out_7710363422868589643[3] = 0;
   out_7710363422868589643[4] = 0;
   out_7710363422868589643[5] = 0;
   out_7710363422868589643[6] = 0;
   out_7710363422868589643[7] = 0;
   out_7710363422868589643[8] = 0;
   out_7710363422868589643[9] = 0;
   out_7710363422868589643[10] = 1;
   out_7710363422868589643[11] = 0;
   out_7710363422868589643[12] = 0;
   out_7710363422868589643[13] = 0;
   out_7710363422868589643[14] = 0;
   out_7710363422868589643[15] = 0;
   out_7710363422868589643[16] = 0;
   out_7710363422868589643[17] = 0;
   out_7710363422868589643[18] = 0;
   out_7710363422868589643[19] = 0;
   out_7710363422868589643[20] = 1;
   out_7710363422868589643[21] = 0;
   out_7710363422868589643[22] = 0;
   out_7710363422868589643[23] = 0;
   out_7710363422868589643[24] = 0;
   out_7710363422868589643[25] = 0;
   out_7710363422868589643[26] = 0;
   out_7710363422868589643[27] = 0;
   out_7710363422868589643[28] = 0;
   out_7710363422868589643[29] = 0;
   out_7710363422868589643[30] = 1;
   out_7710363422868589643[31] = 0;
   out_7710363422868589643[32] = 0;
   out_7710363422868589643[33] = 0;
   out_7710363422868589643[34] = 0;
   out_7710363422868589643[35] = 0;
   out_7710363422868589643[36] = 0;
   out_7710363422868589643[37] = 0;
   out_7710363422868589643[38] = 0;
   out_7710363422868589643[39] = 0;
   out_7710363422868589643[40] = 1;
   out_7710363422868589643[41] = 0;
   out_7710363422868589643[42] = 0;
   out_7710363422868589643[43] = 0;
   out_7710363422868589643[44] = 0;
   out_7710363422868589643[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_7710363422868589643[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_7710363422868589643[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7710363422868589643[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_7710363422868589643[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_7710363422868589643[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_7710363422868589643[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_7710363422868589643[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_7710363422868589643[53] = -9.8100000000000005*dt;
   out_7710363422868589643[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_7710363422868589643[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_7710363422868589643[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7710363422868589643[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7710363422868589643[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_7710363422868589643[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_7710363422868589643[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_7710363422868589643[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_7710363422868589643[62] = 0;
   out_7710363422868589643[63] = 0;
   out_7710363422868589643[64] = 0;
   out_7710363422868589643[65] = 0;
   out_7710363422868589643[66] = 0;
   out_7710363422868589643[67] = 0;
   out_7710363422868589643[68] = 0;
   out_7710363422868589643[69] = 0;
   out_7710363422868589643[70] = 1;
   out_7710363422868589643[71] = 0;
   out_7710363422868589643[72] = 0;
   out_7710363422868589643[73] = 0;
   out_7710363422868589643[74] = 0;
   out_7710363422868589643[75] = 0;
   out_7710363422868589643[76] = 0;
   out_7710363422868589643[77] = 0;
   out_7710363422868589643[78] = 0;
   out_7710363422868589643[79] = 0;
   out_7710363422868589643[80] = 1;
}
void h_25(double *state, double *unused, double *out_4424746055483597783) {
   out_4424746055483597783[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6926042451386776760) {
   out_6926042451386776760[0] = 0;
   out_6926042451386776760[1] = 0;
   out_6926042451386776760[2] = 0;
   out_6926042451386776760[3] = 0;
   out_6926042451386776760[4] = 0;
   out_6926042451386776760[5] = 0;
   out_6926042451386776760[6] = 1;
   out_6926042451386776760[7] = 0;
   out_6926042451386776760[8] = 0;
}
void h_24(double *state, double *unused, double *out_3903348308188753592) {
   out_3903348308188753592[0] = state[4];
   out_3903348308188753592[1] = state[5];
}
void H_24(double *state, double *unused, double *out_6529397147032917265) {
   out_6529397147032917265[0] = 0;
   out_6529397147032917265[1] = 0;
   out_6529397147032917265[2] = 0;
   out_6529397147032917265[3] = 0;
   out_6529397147032917265[4] = 1;
   out_6529397147032917265[5] = 0;
   out_6529397147032917265[6] = 0;
   out_6529397147032917265[7] = 0;
   out_6529397147032917265[8] = 0;
   out_6529397147032917265[9] = 0;
   out_6529397147032917265[10] = 0;
   out_6529397147032917265[11] = 0;
   out_6529397147032917265[12] = 0;
   out_6529397147032917265[13] = 0;
   out_6529397147032917265[14] = 1;
   out_6529397147032917265[15] = 0;
   out_6529397147032917265[16] = 0;
   out_6529397147032917265[17] = 0;
}
void h_30(double *state, double *unused, double *out_5875377448112480950) {
   out_5875377448112480950[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4604011280831158101) {
   out_4604011280831158101[0] = 0;
   out_4604011280831158101[1] = 0;
   out_4604011280831158101[2] = 0;
   out_4604011280831158101[3] = 0;
   out_4604011280831158101[4] = 1;
   out_4604011280831158101[5] = 0;
   out_4604011280831158101[6] = 0;
   out_4604011280831158101[7] = 0;
   out_4604011280831158101[8] = 0;
}
void h_26(double *state, double *unused, double *out_7504949106878727943) {
   out_7504949106878727943[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3184539132512720536) {
   out_3184539132512720536[0] = 0;
   out_3184539132512720536[1] = 0;
   out_3184539132512720536[2] = 0;
   out_3184539132512720536[3] = 0;
   out_3184539132512720536[4] = 0;
   out_3184539132512720536[5] = 0;
   out_3184539132512720536[6] = 0;
   out_3184539132512720536[7] = 1;
   out_3184539132512720536[8] = 0;
}
void h_27(double *state, double *unused, double *out_576927212177247862) {
   out_576927212177247862[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6778774592631583012) {
   out_6778774592631583012[0] = 0;
   out_6778774592631583012[1] = 0;
   out_6778774592631583012[2] = 0;
   out_6778774592631583012[3] = 1;
   out_6778774592631583012[4] = 0;
   out_6778774592631583012[5] = 0;
   out_6778774592631583012[6] = 0;
   out_6778774592631583012[7] = 0;
   out_6778774592631583012[8] = 0;
}
void h_29(double *state, double *unused, double *out_873704180451635305) {
   out_873704180451635305[0] = state[1];
}
void H_29(double *state, double *unused, double *out_8492137319501134045) {
   out_8492137319501134045[0] = 0;
   out_8492137319501134045[1] = 1;
   out_8492137319501134045[2] = 0;
   out_8492137319501134045[3] = 0;
   out_8492137319501134045[4] = 0;
   out_8492137319501134045[5] = 0;
   out_8492137319501134045[6] = 0;
   out_8492137319501134045[7] = 0;
   out_8492137319501134045[8] = 0;
}
void h_28(double *state, double *unused, double *out_6858216222251452951) {
   out_6858216222251452951[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4872207737138886997) {
   out_4872207737138886997[0] = 1;
   out_4872207737138886997[1] = 0;
   out_4872207737138886997[2] = 0;
   out_4872207737138886997[3] = 0;
   out_4872207737138886997[4] = 0;
   out_4872207737138886997[5] = 0;
   out_4872207737138886997[6] = 0;
   out_4872207737138886997[7] = 0;
   out_4872207737138886997[8] = 0;
}
void h_31(double *state, double *unused, double *out_4699940117768103672) {
   out_4699940117768103672[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6956688413263737188) {
   out_6956688413263737188[0] = 0;
   out_6956688413263737188[1] = 0;
   out_6956688413263737188[2] = 0;
   out_6956688413263737188[3] = 0;
   out_6956688413263737188[4] = 0;
   out_6956688413263737188[5] = 0;
   out_6956688413263737188[6] = 0;
   out_6956688413263737188[7] = 0;
   out_6956688413263737188[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_949748206832459961) {
  err_fun(nom_x, delta_x, out_949748206832459961);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3637275118739236570) {
  inv_err_fun(nom_x, true_x, out_3637275118739236570);
}
void car_H_mod_fun(double *state, double *out_2022350626202111920) {
  H_mod_fun(state, out_2022350626202111920);
}
void car_f_fun(double *state, double dt, double *out_311349171040061963) {
  f_fun(state,  dt, out_311349171040061963);
}
void car_F_fun(double *state, double dt, double *out_7710363422868589643) {
  F_fun(state,  dt, out_7710363422868589643);
}
void car_h_25(double *state, double *unused, double *out_4424746055483597783) {
  h_25(state, unused, out_4424746055483597783);
}
void car_H_25(double *state, double *unused, double *out_6926042451386776760) {
  H_25(state, unused, out_6926042451386776760);
}
void car_h_24(double *state, double *unused, double *out_3903348308188753592) {
  h_24(state, unused, out_3903348308188753592);
}
void car_H_24(double *state, double *unused, double *out_6529397147032917265) {
  H_24(state, unused, out_6529397147032917265);
}
void car_h_30(double *state, double *unused, double *out_5875377448112480950) {
  h_30(state, unused, out_5875377448112480950);
}
void car_H_30(double *state, double *unused, double *out_4604011280831158101) {
  H_30(state, unused, out_4604011280831158101);
}
void car_h_26(double *state, double *unused, double *out_7504949106878727943) {
  h_26(state, unused, out_7504949106878727943);
}
void car_H_26(double *state, double *unused, double *out_3184539132512720536) {
  H_26(state, unused, out_3184539132512720536);
}
void car_h_27(double *state, double *unused, double *out_576927212177247862) {
  h_27(state, unused, out_576927212177247862);
}
void car_H_27(double *state, double *unused, double *out_6778774592631583012) {
  H_27(state, unused, out_6778774592631583012);
}
void car_h_29(double *state, double *unused, double *out_873704180451635305) {
  h_29(state, unused, out_873704180451635305);
}
void car_H_29(double *state, double *unused, double *out_8492137319501134045) {
  H_29(state, unused, out_8492137319501134045);
}
void car_h_28(double *state, double *unused, double *out_6858216222251452951) {
  h_28(state, unused, out_6858216222251452951);
}
void car_H_28(double *state, double *unused, double *out_4872207737138886997) {
  H_28(state, unused, out_4872207737138886997);
}
void car_h_31(double *state, double *unused, double *out_4699940117768103672) {
  h_31(state, unused, out_4699940117768103672);
}
void car_H_31(double *state, double *unused, double *out_6956688413263737188) {
  H_31(state, unused, out_6956688413263737188);
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
